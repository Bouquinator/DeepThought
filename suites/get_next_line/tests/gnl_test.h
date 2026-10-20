/* Shared helpers for the get_next_line suite. */
#ifndef GNL_TEST_H
# define GNL_TEST_H
# include "dt.h"
# include <fcntl.h>
# include <stdio.h>
# include <string.h>
# include <unistd.h>
# ifdef GNL_BONUS
#  include "get_next_line_bonus.h"
# else
#  include "get_next_line.h"
# endif

/* The expected lines of a file: split after every '\n'. */
typedef struct s_lines
{
	char	*data;
	size_t	count;
	char	**line;
}	t_lines;

static inline t_lines	read_lines(const char *path)
{
	t_lines	l = {0};
	FILE	*f = fopen(path, "rb");
	long	size;
	size_t	i;
	size_t	start;

	if (!f)
		return (l);
	fseek(f, 0, SEEK_END);
	size = ftell(f);
	fseek(f, 0, SEEK_SET);
	l.data = dt_raw_malloc((size_t)size + 1);
	size = (long)fread(l.data, 1, (size_t)size, f);
	l.data[size] = 0;
	fclose(f);
	l.line = dt_raw_malloc(sizeof(char *) * ((size_t)size + 2));
	start = 0;
	for (i = 0; i < (size_t)size; i++)
		if (l.data[i] == '\n')
		{
			l.line[l.count++] = l.data + start;
			start = i + 1;
		}
	if (start < (size_t)size)
		l.line[l.count++] = l.data + start;
	return (l);
}

static inline size_t	line_len(t_lines *l, size_t i)
{
	char	*nl = strchr(l->line[i], '\n');

	return (nl ? (size_t)(nl - l->line[i]) + 1 : strlen(l->line[i]));
}

/* Read the whole fd with get_next_line and compare every line. */
static inline void	expect_lines(int fd, const char *path)
{
	t_lines	l = read_lines(path);
	char	*got;
	size_t	i;
	char	what[64];

	for (i = 0; i < l.count; i++)
	{
		got = get_next_line(fd);
		snprintf(what, sizeof(what), "line %zu", i + 1);
		if (!got)
		{
			dt_check(0, 0, what, l.line[i], "NULL (returned too early)", __FILE__, __LINE__);
			return ;
		}
		if (!dt_check_bytes(got, strlen(got), l.line[i], line_len(&l, i), 0, what, __FILE__, __LINE__))
		{
			free(got);
			dt_leaks_ignore();
			return ;
		}
		free(got);
	}
	got = get_next_line(fd);
	dt_check(got == NULL, 0, "after the last line", "NULL", got ? got : "", __FILE__, __LINE__);
	free(got);
	dt_raw_free(l.line);
	dt_raw_free(l.data);
}

static inline void	expect_file(const char *name)
{
	int	fd = open(dt_fixture(name), O_RDONLY);

	dt_input("reading the file fixtures/%s with BUFFER_SIZE=%ld", name, (long)BUFFER_SIZE);

	if (fd < 0)
	{
		DT_FAIL("fixture missing");
		return ;
	}
	expect_lines(fd, dt_fixture(name));
	close(fd);
}
#endif
