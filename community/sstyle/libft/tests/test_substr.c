#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_substr, start_0, "start=0")
{
	char	*r;

	r = ft_substr("Hello, World", 0, 5);
	DT_CHECK_STR("substr(\"Hello, World\",0,5)", r, "Hello");
	free(r);
}

DT_TEST(ft_substr, start_in_the_middle, "start in the middle")
{
	char	*r;

	r = ft_substr("Hello, World", 7, 5);
	DT_CHECK_STR("substr(\"Hello, World\",7,5)", r, "World");
	free(r);
}

DT_TEST(ft_substr, len_0_to_empty_string, "len=0 → empty string")
{
	char	*r;

	r = ft_substr("Hello", 0, 0);
	DT_CHECK_STR("substr(\"Hello\",0,0)", r, "");
	free(r);
}

DT_TEST(ft_substr, len_gt_remaining_to_clamp_to, "len > remaining → clamp to rest of string")
{
	char	*r;

	r = ft_substr("Hello", 2, 100);
	DT_CHECK_STR("substr(\"Hello\",2,100)", r, "llo");
	free(r);
}

DT_TEST(ft_substr, start_exactly_at_nul_index_5, "start exactly at NUL (index 5 of \"hello\") → empty string")
{
	char	*r;

	r = ft_substr("hello", 5, 1);
	DT_CHECK_STR("substr(\"hello\",5,1)", r, "");
	free(r);
}

DT_TEST(ft_substr, start_beyond_end_to_empty_string, "start beyond end → empty string")
{
	char	*r;

	r = ft_substr("Hello", 10, 3);
	DT_CHECK_STR("substr(\"Hello\",10,3)", r, "");
	free(r);
}

DT_TEST(ft_substr, start_uint_max_to_start_len, "start = UINT_MAX → start + len overflows if done naively")
{
	char	*r;

	r = ft_substr("hello", (unsigned int)-1, 5);
	DT_CHECK_STR("substr(UINT_MAX,5)", r, "");
	free(r);
}

DT_TEST(ft_substr, null_string_to_null_return_without, "NULL string → NULL return without crash")
{
	char	*r;

	r = ft_substr(NULL, 0, 5);
	if (!(r == NULL))
	{
		DT_FAILF("substr(NULL,0,5) → expected NULL");
		free(r);
	}
}
