#include "libft.h"

char	*ft_substr(char const *s, unsigned int start, size_t len)
{
	size_t sl;
	char *r;
	if (!s) return (NULL);
	sl = ft_strlen(s);
	if (start >= sl) return (ft_strdup(""));
	if (len > sl - start) len = sl - start;
	r = malloc(len + 1);
	if (!r) return (NULL);
	ft_strlcpy(r, s + start, len + 1);
	return (r);
}
char	*ft_strjoin(char const *s1, char const *s2)
{
	size_t a, b;
	char *r;
	if (!s1 || !s2) return (NULL);
	a = ft_strlen(s1); b = ft_strlen(s2);
	r = malloc(a + b + 1);
	if (!r) return (NULL);
	ft_memcpy(r, s1, a); ft_memcpy(r + a, s2, b + 1);
	return (r);
}
char	*ft_strtrim(char const *s1, char const *set)
{
	size_t start = 0, end;
	if (!s1 || !set) return (NULL);
	end = ft_strlen(s1);
	while (s1[start] && ft_strchr(set, s1[start])) start++;
	while (end > start && ft_strchr(set, s1[end - 1])) end--;
	return (ft_substr(s1, start, end - start));
}
static size_t	count_words(char const *s, char c)
{
	size_t n = 0;
	while (*s) { while (*s == c) s++; if (*s) n++; while (*s && *s != c) s++; }
	return (n);
}
char	**ft_split(char const *s, char c)
{
	char **r; size_t i = 0, len;
	if (!s) return (NULL);
	r = malloc(sizeof(char *) * (count_words(s, c) + 1));
	if (!r) return (NULL);
	while (*s)
	{
		while (*s == c) s++;
		if (!*s) break ;
		len = 0;
		while (s[len] && s[len] != c) len++;
		r[i] = ft_substr(s, 0, len);
		if (!r[i]) { while (i > 0) free(r[--i]); free(r); return (NULL); }
		i++; s += len;
	}
	r[i] = NULL;
	return (r);
}
char	*ft_itoa(int n)
{
	char buf[12]; int i = 11; long v = n;
	buf[i] = 0;
	if (v == 0) buf[--i] = '0';
	if (v < 0) v = -v;
	while (v) { buf[--i] = '0' + v % 10; v /= 10; }
	if (n < 0) buf[--i] = '-';
	return (ft_strdup(buf + i));
}
char	*ft_strmapi(char const *s, char (*f)(unsigned int, char))
{
	char *r; unsigned int i = 0;
	if (!s || !f) return (NULL);
	r = ft_strdup(s);
	if (!r) return (NULL);
	while (r[i]) { r[i] = f(i, r[i]); i++; }
	return (r);
}
void	ft_striteri(char *s, void (*f)(unsigned int, char *))
{
	unsigned int i = 0;
	if (!s || !f) return ;
	while (s[i]) { f(i, &s[i]); i++; }
}
void	ft_putchar_fd(char c, int fd) { write(fd, &c, 1); }
void	ft_putstr_fd(char *s, int fd) { if (s) write(fd, s, ft_strlen(s)); }
void	ft_putendl_fd(char *s, int fd) { ft_putstr_fd(s, fd); write(fd, "\n", 1); }
void	ft_putnbr_fd(int n, int fd)
{
	long v = n;
	if (v < 0) { ft_putchar_fd('-', fd); v = -v; }
	if (v >= 10) ft_putnbr_fd((int)(v / 10), fd);
	ft_putchar_fd('0' + v % 10, fd);
}
