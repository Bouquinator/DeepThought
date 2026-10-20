#include "libft.h"
#include <stdint.h>

int	ft_isalpha(int c) { return ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')); }
int	ft_isdigit(int c) { return (c >= '0' && c <= '9'); }
int	ft_isalnum(int c) { return (ft_isalpha(c) || ft_isdigit(c)); }
int	ft_isascii(int c) { return (c >= 0 && c <= 127); }
int	ft_isprint(int c) { return (c >= 32 && c <= 126); }
size_t	ft_strlen(const char *s) { size_t i = 0; while (s[i]) i++; return (i); }
void	*ft_memset(void *s, int c, size_t n) { unsigned char *p = s; while (n--) *p++ = (unsigned char)c; return (s); }
void	ft_bzero(void *s, size_t n) { ft_memset(s, 0, n); }
void	*ft_memcpy(void *dst, const void *src, size_t n)
{
	unsigned char *d = dst; const unsigned char *s = src;
	if (!dst && !src) return (dst);
	while (n--) *d++ = *s++;
	return (dst);
}
void	*ft_memmove(void *dst, const void *src, size_t n)
{
	unsigned char *d = dst; const unsigned char *s = src;
	if (d == s || n == 0) return (dst);
	if (d < s) while (n--) *d++ = *s++;
	else while (n--) d[n] = s[n];
	return (dst);
}
size_t	ft_strlcpy(char *dst, const char *src, size_t size)
{
	size_t i = 0, len = ft_strlen(src);
	if (size == 0) return (len);
	while (src[i] && i < size - 1) { dst[i] = src[i]; i++; }
	dst[i] = 0;
	return (i);
}
size_t	ft_strlcat(char *dst, const char *src, size_t size)
{
	size_t dl = 0, sl = ft_strlen(src), i = 0;
	while (dl < size && dst[dl]) dl++;
	if (dl == size) return (size + sl);
	while (src[i] && dl + i < size - 1) { dst[dl + i] = src[i]; i++; }
	dst[dl + i] = 0;
	return (dl + sl);
}
int	ft_toupper(int c) { return ((c >= 'a' && c <= 'z') ? c - 32 : c); }
int	ft_tolower(int c) { return ((c >= 'A' && c <= 'Z') ? c + 32 : c); }
char	*ft_strchr(const char *s, int c)
{
	while (*s) { if (*s == (char)c) return ((char *)s); if (*s != ' ') s++; }
	return ((char)c == 0 ? (char *)s : NULL);
}
char	*ft_strrchr(const char *s, int c)
{
	const char *r = NULL;
	while (*s) { if (*s == (char)c) r = s; s++; }
	return ((char)c == 0 ? (char *)s : (char *)r);
}
int	ft_strncmp(const char *s1, const char *s2, size_t n)
{
	size_t i = 0;
	while (i < n && (s1[i] || s2[i]))
	{
		if (s1[i] != s2[i]) return ((unsigned char)s1[i] - (unsigned char)s2[i]);
		i++;
	}
	return (0);
}
void	*ft_memchr(const void *s, int c, size_t n)
{
	const unsigned char *p = s;
	while (n--) { if (*p == (unsigned char)c) return ((void *)p); p++; }
	return (NULL);
}
int	ft_memcmp(const void *s1, const void *s2, size_t n)
{
	const unsigned char *a = s1, *b = s2;
	while (n--) { if (*a != *b) return (*a - *b); a++; b++; }
	return (0);
}
int	ft_atoi(const char *s)
{
	long r = 0; int sign = 1;
	while (*s == ' ' || (*s >= 9 && *s <= 13)) s++;
	if (*s == '-' || *s == '+') { s++; }
	while (*s >= '0' && *s <= '9') r = r * 10 + (*s++ - '0');
	return ((int)(r * sign));
}
void	*ft_calloc(size_t nmemb, size_t size)
{
	void *p;
	p = malloc(nmemb * size);
	if (p) ft_bzero(p, nmemb * size);
	return (p);
}
char	*ft_strdup(const char *s)
{
	size_t n = ft_strlen(s) + 1;
	char *d = malloc(n);
	while (n--) d[n] = s[n];
	return (d);
}
