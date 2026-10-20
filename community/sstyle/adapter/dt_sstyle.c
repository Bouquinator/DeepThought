/*
** DeepThought adapter for SStyles93's CodeTester
** (https://github.com/SStyles93/42_CodeTester).
**
** The CodeTester's own sources (src/utils.c, src/runner.c, src/memcheck.c and
** every tests/ file) are compiled unmodified; this file replaces only its
** command-line entry point (src/main.c, src/menu.c). Every CodeTester suite
** becomes one DeepThought test: it is run with the CodeTester's own
** run_suite() in verbose mode, and each "✗" line of its report becomes a
** DeepThought failure with expected / actual values. The full report is kept
** as the test's output.
**
** Environment:
**   SSTYLE_SELECT   comma-separated patterns of "Project/suite" to expose,
**                   "!" excludes: "Libft/ft_*,!Libft/ft_lst?*" (fnmatch)
**   SSTYLE_TIMEOUT  the CodeTester's own per-suite timeout (seconds)
*/

#include "dt.h"
#include "tester.h"
#include <dirent.h>
#include <fnmatch.h>

#ifndef SSTYLE_ROOT
# define SSTYLE_ROOT "."
#endif
#define MAX_SUITES 256

typedef struct s_entry
{
	t_project	*project;
	t_suite		*suite;
	char		id[256];
	char		desc[512];
	char		file[1024];
	int			line;
}	t_entry;

static t_entry	g_entries[MAX_SUITES];
static int		g_count;

/* ------------------------------------------------------------ selection */

static int	selected(const char *id)
{
	const char	*sel = getenv("SSTYLE_SELECT");
	char		buf[2048];
	char		*tok;
	char		*save;
	int			keep = 0;
	int			any_include = 0;

	if (!sel || !*sel)
		return (1);
	snprintf(buf, sizeof(buf), "%s", sel);
	for (tok = strtok_r(buf, ",", &save); tok; tok = strtok_r(NULL, ",", &save))
	{
		while (*tok == ' ')
			tok++;
		if (*tok == '!')
		{
			if (fnmatch(tok + 1, id, 0) == 0)
				return (0);
			continue ;
		}
		any_include = 1;
		if (fnmatch(tok, id, 0) == 0)
			keep = 1;
	}
	return (keep || !any_include);
}

/* ------------------------------------------------------------ source lookup */

/* Find where a suite's test function is defined, so the UI can show it. */
static int	scan_file(const char *path, const char *needle, int definition)
{
	FILE	*f = fopen(path, "r");
	char	line[4096];
	int		n = 0;

	if (!f)
		return (0);
	while (fgets(line, sizeof(line), f))
	{
		n++;
		if (strstr(line, needle) && (!definition
				|| (strncmp(line, "void", 4) == 0 && !strchr(line, ';'))))
		{
			fclose(f);
			return (n);
		}
	}
	fclose(f);
	return (0);
}

static void	function_of(const char *suite, char *fn, size_t size)
{
	char			path[1024];
	char			needle[300];
	char			line[4096];
	const char		*dirs[] = {"tests/libft", "tests/printf", "tests", NULL};
	FILE			*f;
	int				i;

	fn[0] = 0;
	snprintf(needle, sizeof(needle), "{\"%s\",", suite);
	for (i = 0; dirs[i] && !fn[0]; i++)
	{
		snprintf(path, sizeof(path), "%s/%s/registry.c", SSTYLE_ROOT, dirs[i]);
		if (!(f = fopen(path, "r")))
			continue ;
		while (fgets(line, sizeof(line), f))
		{
			char	*p = strstr(line, needle);

			if (p && sscanf(p + strlen(needle), " %255[A-Za-z0-9_]", fn) == 1)
				break ;
			fn[0] = 0;
		}
		fclose(f);
	}
	(void)size;
}

static void	locate(t_entry *en)
{
	char			fn[256];
	char			needle[300];
	char			dir[1024];
	char			path[2048];
	const char		*dirs[] = {"tests/libft", "tests/printf", NULL};
	DIR				*d;
	struct dirent	*e;
	int				i;
	int				line;

	function_of(en->suite->name, fn, sizeof(fn));
	if (!fn[0])
		return ;
	snprintf(needle, sizeof(needle), "%s(t_ctx", fn);
	for (i = 0; dirs[i]; i++)
	{
		snprintf(dir, sizeof(dir), "%s/%s", SSTYLE_ROOT, dirs[i]);
		if (!(d = opendir(dir)))
			continue ;
		while ((e = readdir(d)))
		{
			if (!strstr(e->d_name, ".c") || !strcmp(e->d_name, "registry.c"))
				continue ;
			snprintf(path, sizeof(path), "%s/%s", dir, e->d_name);
			if ((line = scan_file(path, needle, 1)))
			{
				snprintf(en->file, sizeof(en->file), "%s", path);
				en->line = line;
				closedir(d);
				return ;
			}
		}
		closedir(d);
	}
}

/* ------------------------------------------------------------ report parsing */

static void	strip_ansi(char *s)
{
	char	*w = s;

	while (*s)
	{
		if (*s == '\033' && s[1] == '[')
		{
			s += 2;
			while (*s && !((*s >= 'A' && *s <= 'Z') || (*s >= 'a' && *s <= 'z')))
				s++;
			if (*s)
				s++;
			continue ;
		}
		*w++ = *s++;
	}
	*w = 0;
}

static char	*trim(char *s)
{
	char	*end;

	while (*s == ' ' || *s == '\t')
		s++;
	end = s + strlen(s);
	while (end > s && (end[-1] == ' ' || end[-1] == '\n' || end[-1] == '\r'))
		*--end = 0;
	return (s);
}

/* "\"a\\nb\" return 3" -> bytes a\nb (the CodeTester's escaped form). */
static size_t	unquote(const char *src, char *dst, size_t cap, const char **rest)
{
	size_t	n = 0;

	if (*src != '"')
	{
		snprintf(dst, cap, "%s", src);
		if (rest)
			*rest = src + strlen(src);
		return (strlen(dst));
	}
	src++;
	while (*src && *src != '"' && n + 1 < cap)
	{
		if (*src == '\\' && src[1])
		{
			src++;
			if (*src == 'n')
				dst[n++] = '\n';
			else if (*src == 't')
				dst[n++] = '\t';
			else if (*src == 'x' && src[1] && src[2])
			{
				char	hex[3] = {src[1], src[2], 0};

				dst[n++] = (char)strtol(hex, NULL, 16);
				src += 2;
			}
			else
				dst[n++] = *src;
			src++;
		}
		else
			dst[n++] = *src++;
	}
	if (*src == '"')
		src++;
	dst[n] = 0;
	if (rest)
		*rest = src;
	return (n);
}

/* Split "LABEL → expected A, got B" / "LABEL: expected A, got B". */
static void	split_expected(char *text, char **msg, char **exp, char **got)
{
	char	*sep = strstr(text, " → expected ");
	size_t	skip = strlen(" → expected ");
	char	*g;

	if (!sep)
	{
		sep = strstr(text, ": expected ");
		skip = strlen(": expected ");
	}
	*msg = text;
	*exp = "";
	*got = "";
	if (!sep)
		return ;
	*sep = 0;
	*exp = sep + skip;
	g = strstr(*exp, ", got ");
	if (g)
	{
		*g = 0;
		*got = g + strlen(", got ");
	}
}

/* Every "✗" line is a failure, even when expected and got look identical. */
static void	failure(const char *msg, const char *e, size_t el, const char *g, size_t gl)
{
	if (el == gl && (el == 0 || memcmp(e, g, el) == 0))
		dt_check(0, 0, msg, el ? e : "(see the report below)", el ? g : "", "", 0);
	else
		dt_check_bytes(g, gl, e, el, 0, msg, "", 0);
}

/* "ft_split               3/12" (the suite's summary line, after the mark) */
static int	is_summary(const char *t, const char *name)
{
	size_t	n = strlen(name);

	if (strncmp(t, name, n) != 0 || t[n] != ' ')
		return (0);
	t += n;
	while (*t == ' ')
		t++;
	return (*t && strspn(t, "0123456789/") == strlen(t));
}

static void	report(char *out, const char *suite)
{
	static char	*lines[16384];
	int			n = 0;
	int			i;
	char		*save;
	char		*l;

	for (l = strtok_r(out, "\n", &save); l && n < 16384; l = strtok_r(NULL, "\n", &save))
		lines[n++] = l;
	for (i = 0; i < n; i++)
	{
		char	*t = trim(lines[i]);
		char	*msg;
		char	*exp;
		char	*got;

		if (t[0] == '?' && strstr(t, " MISSING"))
		{
			dt_check(0, 0, "function not implemented (MISSING)", "a definition", "missing", "", 0);
			continue ;
		}
		if (strncmp(t, "✗ ", strlen("✗ ")) != 0)
			continue ;
		t += strlen("✗ ");
		if (is_summary(t, suite))
			continue ;
		if (i + 2 < n && strncmp(trim(lines[i + 1]), "expected:", 9) == 0
			&& strncmp(trim(lines[i + 2]), "got:", 4) == 0)
		{
			static char	e[65536];
			static char	g[65536];
			char		label[1024];
			const char	*rest;
			size_t		el;
			size_t		gl;
			int			er = 0;
			int			gr = 0;

			el = unquote(trim(trim(lines[i + 1]) + 9), e, sizeof(e), &rest);
			sscanf(rest, " return %d", &er);
			gl = unquote(trim(trim(lines[i + 2]) + 4), g, sizeof(g), &rest);
			sscanf(rest, " return %d", &gr);
			snprintf(label, sizeof(label), "%s   (return: expected %d, got %d)", t, er, gr);
			failure(label, e, el, g, gl);
			i += 2;
			continue ;
		}
		split_expected(t, &msg, &exp, &got);
		{
			static char	e[8192];
			static char	g[8192];
			size_t		el = unquote(exp, e, sizeof(e), NULL);
			size_t		gl = unquote(got, g, sizeof(g), NULL);

			failure(msg, e, el, g, gl);
		}
	}
}

/* ------------------------------------------------------------ running */

static void	run_entry(int i)
{
	t_dt_capture	cap;
	const char		*to = getenv("SSTYLE_TIMEOUT");
	char			*text;

	if (to && atoi(to) > 0)
		g_test_timeout = atoi(to);
	DT_CAPTURE_STDOUT(cap, run_suite(g_entries[i].project, g_entries[i].suite, 1));
	if (!cap.data)
	{
		DT_FAIL("the suite produced no report");
		return ;
	}
	strip_ansi(cap.data);
	write(1, cap.data, strlen(cap.data));
	text = dt_raw_malloc(strlen(cap.data) + 1);
	if (text)
	{
		strcpy(text, cap.data);
		report(text, g_entries[i].suite->name);
		dt_raw_free(text);
	}
	/* the summary line decides: "✗ name a/b" means at least one check failed */
	{
		char	needle[300];
		char	*p;

		snprintf(needle, sizeof(needle), "✗ %s ", g_entries[i].suite->name);
		p = strstr(cap.data, needle);
		if (p)
			dt_note("CodeTester summary: %s", trim(p + strlen("✗ ")));
		snprintf(needle, sizeof(needle), "~ %s ", g_entries[i].suite->name);
		if ((p = strstr(cap.data, needle)))
			dt_note("informational (differs from the original printf): %s", trim(p + 2));
	}
	dt_capture_free(&cap);
}

/* one trampoline per possible suite: 4 x 8 x 8 = 256 */
#define T(a, b, c) static void tramp_##a##_##b##_##c(void) { run_entry((a) * 64 + (b) * 8 + (c)); }
#define T8(a, b) T(a, b, 0) T(a, b, 1) T(a, b, 2) T(a, b, 3) T(a, b, 4) T(a, b, 5) T(a, b, 6) T(a, b, 7)
#define T64(a) T8(a, 0) T8(a, 1) T8(a, 2) T8(a, 3) T8(a, 4) T8(a, 5) T8(a, 6) T8(a, 7)
T64(0) T64(1) T64(2) T64(3)
#define P(a, b, c) tramp_##a##_##b##_##c,
#define P8(a, b) P(a, b, 0) P(a, b, 1) P(a, b, 2) P(a, b, 3) P(a, b, 4) P(a, b, 5) P(a, b, 6) P(a, b, 7)
#define P64(a) P8(a, 0) P8(a, 1) P8(a, 2) P8(a, 3) P8(a, 4) P8(a, 5) P8(a, 6) P8(a, 7)

static void	(*g_tramps[MAX_SUITES])(void) = {P64(0) P64(1) P64(2) P64(3)};

__attribute__((constructor)) static void	sstyle_register(void)
{
	t_project	**projects;
	int			count;
	int			p;
	int			s;
	int			ntramps = (int)(sizeof(g_tramps) / sizeof(g_tramps[0]));

	projects = get_all_projects(&count);
	for (p = 0; p < count; p++)
		for (s = 0; s < projects[p]->suite_count && g_count < ntramps; s++)
		{
			t_entry	*en = &g_entries[g_count];

			en->project = projects[p];
			en->suite = &projects[p]->suites[s];
			snprintf(en->id, sizeof(en->id), "%s/%s", projects[p]->name, en->suite->name);
			if (!selected(en->id))
				continue ;
			snprintf(en->desc, sizeof(en->desc), "CodeTester suite %s (%s)%s",
				en->suite->name, projects[p]->name,
				projects[p]->informational ? ", informational" : "");
			locate(en);
			dt_register((t_dt_test){projects[p]->name, en->suite->name, en->desc,
				en->file[0] ? en->file : "", en->line, g_tramps[g_count]});
			g_count++;
		}
}
