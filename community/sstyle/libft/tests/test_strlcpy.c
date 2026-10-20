#include "sstyle.h"
#include <string.h>

DT_TEST(ft_strlcpy, basic_copy_enough_space, "basic copy, enough space")
{
	char	dst[20];
	size_t	ret;

	ret = ft_strlcpy(dst, "Hello", 20);
	DT_CHECK_SIZE("return = src len (5)", ret, 5);
	DT_CHECK_STR("basic copy result", dst, "Hello");
}

DT_TEST(ft_strlcpy, exact_fit, "exact fit: size == strlen(src) + 1")
{
	char	dst[20];
	size_t	ret;

	ret = ft_strlcpy(dst, "Hello", 6);
	DT_CHECK_SIZE("exact fit return (5)", ret, 5);
	DT_CHECK_STR("exact fit result", dst, "Hello");
}

DT_TEST(ft_strlcpy, truncation, "truncation: size smaller than src")
{
	char	dst[20];
	size_t	ret;

	ret = ft_strlcpy(dst, "Hello, World!", 6);
	DT_CHECK_SIZE("truncated return = full src len (13)", ret, 13);
	DT_CHECK_STR("truncated to 5 + NUL", dst, "Hello");
}

DT_TEST(ft_strlcpy, size_1, "size=1: only NUL written")
{
	char	dst[20];
	size_t	ret;

	strcpy(dst, "XXXX");
	ret = ft_strlcpy(dst, "Hello", 1);
	DT_CHECK_SIZE("size=1 return (5)", ret, 5);
	DT_CHECK_STR("size=1 result is empty string", dst, "");
}

DT_TEST(ft_strlcpy, size_0, "size=0: no write at all")
{
	char	dst[20];
	size_t	ret;

	strcpy(dst, "XXXX");
	ret = ft_strlcpy(dst, "Hello", 0);
	DT_CHECK_SIZE("size=0 return (5)", ret, 5);
	DT_CHECK_STR("size=0 dst unchanged", dst, "XXXX");
}
