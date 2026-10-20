#include "get_next_line.h"

size_t	gnl_strlen(const char *s)
{
	size_t	i = 0;

	while (s && s[i])
		i++;
	return (i);
}

char	*gnl_strchr(const char *s, int c)
{
	while (s && *s)
	{
		if (*s == (char)c)
			return ((char *)s);
		s++;
	}
	return (NULL);
}

char	*gnl_join(char *stash, const char *buf, size_t n)
{
	size_t	a = gnl_strlen(stash);
	size_t	i = 0;
	char	*r = malloc(a + n + 1);

	if (!r)
		return (free(stash), NULL);
	while (i < a)
	{
		r[i] = stash[i];
		i++;
	}
	while (i < a + n)
	{
		r[i] = buf[i - a];
		i++;
	}
	r[i] = 0;
	free(stash);
	return (r);
}
