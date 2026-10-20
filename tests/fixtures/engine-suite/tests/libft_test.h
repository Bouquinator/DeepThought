/* Shared helpers for the libft suite. */
#ifndef LIBFT_TEST_H
# define LIBFT_TEST_H
# include "dt.h"
# include "libft.h"
# include <ctype.h>
# include <limits.h>
# include <string.h>
# include <stdint.h>

/* portable references (strlcpy & co are not in every libc) */
static inline size_t	ref_strlcpy(char *d, const char *s, size_t n)
{
	size_t	l = strlen(s);

	if (n)
	{
		size_t c = l >= n ? n - 1 : l;
		memcpy(d, s, c);
		d[c] = 0;
	}
	return (l);
}

static inline size_t	ref_strlcat(char *d, const char *s, size_t n)
{
	size_t	dl = 0;

	while (dl < n && d[dl])
		dl++;
	if (dl == n)
		return (n + strlen(s));
	return (dl + ref_strlcpy(d + dl, s, n - dl));
}

static inline char	*ref_strnstr(const char *h, const char *n, size_t len)
{
	size_t	nl = strlen(n);
	size_t	i = 0;

	if (!nl)
		return ((char *)h);
	while (i < len && h[i])
	{
		if (i + nl <= len && !strncmp(h + i, n, nl))
			return ((char *)h + i);
		i++;
	}
	return (NULL);
}

static inline void	free_split(char **tab)
{
	size_t	i = 0;

	while (tab && tab[i])
		free(tab[i++]);
	free(tab);
}
#endif
