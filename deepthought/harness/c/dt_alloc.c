/*
** dt_alloc.c — malloc/free interposition for leak detection and
** malloc-failure injection, without valgrind.
**
** Only allocations made by code linked into the test binary (the student's
** library and the tests) are tracked; libc-internal allocations are ignored.
** Build with -DDT_NO_ALLOC_HOOK (e.g. for sanitizer builds) to disable.
*/

#ifndef _GNU_SOURCE
# define _GNU_SOURCE
#endif
#include "dt.h"
#include <stdint.h>

#define DT_TABLE_SIZE 65536

typedef struct s_dt_slot
{
	void	*ptr;
	size_t	size;
}	t_dt_slot;

static t_dt_slot	g_table[DT_TABLE_SIZE];
static int			g_tracking = 0;
static int			g_overflow = 0;
static int			g_ignore_leaks = 0;
static int			g_calls = 0;
static int			g_fail_at = 0;
static int			g_fail_all = 0;

#ifdef DT_NO_ALLOC_HOOK

void	*dt_raw_malloc(size_t size) { return (malloc(size)); }
void	dt_raw_free(void *ptr) { free(ptr); }
int		dt_alloc_hooked(void) { return (0); }
void	dt_alloc_start(void) {}
void	dt_alloc_stop(void) {}
int		dt_alloc_leaks(size_t *b, size_t *c) { *b = 0; *c = 0; return (0); }
void	dt_malloc_fail_at(int n) { (void)n; dt_skip("malloc hooks are disabled (sanitizer build)"); }
void	dt_malloc_fail_all(void) { dt_skip("malloc hooks are disabled (sanitizer build)"); }
void	dt_malloc_reset(void) {}
int		dt_malloc_calls(void) { return (-1); }
void	dt_leaks_ignore(void) {}
size_t	dt_alloc_size(const void *p) { (void)p; return (0); }
size_t	dt_alloc_live(void) { return (0); }

#else

# include <dlfcn.h>

# if defined(__GLIBC__)

extern void	*__libc_malloc(size_t size);
extern void	__libc_free(void *ptr);
extern void	*__libc_calloc(size_t n, size_t size);
extern void	*__libc_realloc(void *ptr, size_t size);
extern char	__executable_start;
extern char	etext;
#  define REAL_MALLOC(s) __libc_malloc(s)
#  define REAL_FREE(p) __libc_free(p)
#  define REAL_CALLOC(n, s) __libc_calloc(n, s)
#  define REAL_REALLOC(p, s) __libc_realloc(p, s)

/* on glibc our malloc interposes the whole process: only track callers
** living in the test executable itself */
static int	from_exe(void *ret)
{
	return ((char *)ret >= &__executable_start && (char *)ret < &etext);
}

# else

/* macOS (two-level namespace): only code in this image reaches these
** definitions, so every call is ours. */
static void	*(*g_real_malloc)(size_t);
static void	(*g_real_free)(void *);
static void	*(*g_real_calloc)(size_t, size_t);
static void	*(*g_real_realloc)(void *, size_t);

static void	resolve(void)
{
	if (g_real_malloc)
		return ;
	g_real_malloc = (void *(*)(size_t))dlsym(RTLD_NEXT, "malloc");
	g_real_free = (void (*)(void *))dlsym(RTLD_NEXT, "free");
	g_real_calloc = (void *(*)(size_t, size_t))dlsym(RTLD_NEXT, "calloc");
	g_real_realloc = (void *(*)(void *, size_t))dlsym(RTLD_NEXT, "realloc");
}
#  define REAL_MALLOC(s) (resolve(), g_real_malloc(s))
#  define REAL_FREE(p) (resolve(), g_real_free(p))
#  define REAL_CALLOC(n, s) (resolve(), g_real_calloc(n, s))
#  define REAL_REALLOC(p, s) (resolve(), g_real_realloc(p, s))

static int	from_exe(void *ret)
{
	(void)ret;
	return (1);
}

# endif

static size_t	slot_of(const void *ptr)
{
	uintptr_t	h;

	h = (uintptr_t)ptr;
	h ^= h >> 17;
	h *= 0x9E3779B97F4A7C15ULL;
	return ((size_t)(h >> 7) % DT_TABLE_SIZE);
}

static void	track_add(void *ptr, size_t size)
{
	size_t	i;
	size_t	n;

	if (!ptr || !g_tracking)
		return ;
	i = slot_of(ptr);
	n = 0;
	while (g_table[i].ptr && g_table[i].ptr != (void *)1 && n++ < DT_TABLE_SIZE)
		i = (i + 1) % DT_TABLE_SIZE;
	if (n >= DT_TABLE_SIZE)
	{
		g_overflow = 1;
		return ;
	}
	g_table[i].ptr = ptr;
	g_table[i].size = size;
}

static t_dt_slot	*track_find(const void *ptr)
{
	size_t	i;
	size_t	n;

	if (!ptr)
		return (NULL);
	i = slot_of(ptr);
	n = 0;
	while (g_table[i].ptr && n++ < DT_TABLE_SIZE)
	{
		if (g_table[i].ptr == ptr)
			return (&g_table[i]);
		i = (i + 1) % DT_TABLE_SIZE;
	}
	return (NULL);
}

static void	track_remove(const void *ptr)
{
	t_dt_slot	*slot;

	slot = track_find(ptr);
	if (slot)
	{
		slot->ptr = (void *)1;
		slot->size = 0;
	}
}

static int	should_fail(void)
{
	g_calls++;
	if (g_fail_all)
		return (1);
	return (g_fail_at > 0 && g_calls == g_fail_at);
}

void	*malloc(size_t size)
{
	void	*p;

	if (!g_tracking || !from_exe(__builtin_return_address(0)))
		return (REAL_MALLOC(size));
	if (should_fail())
		return (NULL);
	p = REAL_MALLOC(size);
	track_add(p, size);
	return (p);
}

void	*calloc(size_t n, size_t size)
{
	void	*p;

	if (!g_tracking || !from_exe(__builtin_return_address(0)))
		return (REAL_CALLOC(n, size));
	if (should_fail())
		return (NULL);
	p = REAL_CALLOC(n, size);
	track_add(p, n * size);
	return (p);
}

void	*realloc(void *ptr, size_t size)
{
	void	*p;

	if (!g_tracking || !from_exe(__builtin_return_address(0)))
	{
		p = REAL_REALLOC(ptr, size);
		if (p != ptr && track_find(ptr))
		{
			track_remove(ptr);
			track_add(p, size);
		}
		return (p);
	}
	if (should_fail())
		return (NULL);
	p = REAL_REALLOC(ptr, size);
	if (p)
	{
		track_remove(ptr);
		track_add(p, size);
	}
	return (p);
}

void	free(void *ptr)
{
	if (ptr)
		track_remove(ptr);
	REAL_FREE(ptr);
}

void	*dt_raw_malloc(size_t size) { return (REAL_MALLOC(size)); }
void	dt_raw_free(void *ptr) { REAL_FREE(ptr); }
int		dt_alloc_hooked(void) { return (1); }

void	dt_alloc_start(void)
{
	memset(g_table, 0, sizeof(g_table));
	g_overflow = 0;
	g_ignore_leaks = 0;
	g_calls = 0;
	g_fail_at = 0;
	g_fail_all = 0;
	g_tracking = 1;
}

void	dt_alloc_stop(void)
{
	g_tracking = 0;
	g_fail_at = 0;
	g_fail_all = 0;
}

int	dt_alloc_leaks(size_t *bytes, size_t *count)
{
	size_t	i;

	*bytes = 0;
	*count = 0;
	if (g_ignore_leaks || g_overflow)
		return (0);
	i = 0;
	while (i < DT_TABLE_SIZE)
	{
		if (g_table[i].ptr && g_table[i].ptr != (void *)1)
		{
			*bytes += g_table[i].size;
			(*count)++;
		}
		i++;
	}
	return (*count > 0);
}

void	dt_malloc_fail_at(int nth)
{
	g_calls = 0;
	g_fail_all = 0;
	g_fail_at = nth;
}

void	dt_malloc_fail_all(void)
{
	g_calls = 0;
	g_fail_all = 1;
}

void	dt_malloc_reset(void)
{
	g_calls = 0;
	g_fail_at = 0;
	g_fail_all = 0;
}

int	dt_malloc_calls(void)
{
	return (g_calls);
}

void	dt_leaks_ignore(void)
{
	g_ignore_leaks = 1;
}

size_t	dt_alloc_live(void)
{
	size_t	i;
	size_t	n;

	n = 0;
	i = 0;
	while (i < DT_TABLE_SIZE)
	{
		if (g_table[i].ptr && g_table[i].ptr != (void *)1)
			n++;
		i++;
	}
	return (n);
}

size_t	dt_alloc_size(const void *ptr)
{
	t_dt_slot	*slot;

	slot = track_find(ptr);
	if (slot)
		return (slot->size);
	return (0);
}

#endif
