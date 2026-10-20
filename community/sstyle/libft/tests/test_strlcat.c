#include "sstyle.h"
#include <string.h>

/*
** NOTE: ft_strlcat.c calls strlen() without #include <string.h>.
** Add that include to ft_strlcat.c or it will fail to compile with -Werror.
** Also: ft_strlcat uses unsigned int instead of size_t (non-standard).
*/

DT_TEST(ft_strlcat, basic, "basic: \"Hello\" + \" World\" in size 20 → \"Hello World\", returns 11")
{
	char	dst[20];
	unsigned int	ret;

	strcpy(dst, "Hello");
	ret = ft_strlcat(dst, " World", 20);
	DT_CHECK_UINT("return basic (11)", ret, 11);
	DT_CHECK_STR("result basic", dst, "Hello World");
}

DT_TEST(ft_strlcat, size_too_small, "size too small: only partial cat, return still = dst_len + src_len")
{
	char	dst[20];
	unsigned int	ret;

	strcpy(dst, "Hello");
	ret = ft_strlcat(dst, " World", 8);
	DT_CHECK_UINT("truncated return (11)", ret, 11);
	DT_CHECK_STR("truncated result", dst, "Hello W");
}

DT_TEST(ft_strlcat, size_le_dst_len, "size <= dst_len: no write, return = size + src_len")
{
	char	dst[20];
	unsigned int	ret;

	strcpy(dst, "Hello");
	ret = ft_strlcat(dst, " World", 3);
	DT_CHECK_UINT("size<dst_len return (9)", ret, 9);
	DT_CHECK_STR("size<dst_len dst unchanged", dst, "Hello");
}

DT_TEST(ft_strlcat, size_0, "size=0: no write, return = size(0) + strlen(src) = 6")
{
	char	dst[20];
	unsigned int	ret;

	strcpy(dst, "hello");
	ret = ft_strlcat(dst, " world", 0);
	DT_CHECK_UINT("size=0 return (= 0+6=6)", ret, 6);
	DT_CHECK_STR("size=0 dst unchanged", dst, "hello");
}

DT_TEST(ft_strlcat, exact_fit, "exact fit: dst_len + src_len + 1 == size (no truncation)")
{
	char	dst[20];
	unsigned int	ret;

	strcpy(dst, "Hello");
	ret = ft_strlcat(dst, " World", 12);
	DT_CHECK_UINT("exact fit return (11)", ret, 11);
	DT_CHECK_STR("exact fit result", dst, "Hello World");
}
