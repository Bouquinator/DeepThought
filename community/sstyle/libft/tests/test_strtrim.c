#include "sstyle.h"
#include <stdlib.h>

DT_TEST(ft_strtrim, trim_both_sides_with_single_char, "trim both sides with single char")
{
	char	*r;

	r = ft_strtrim("  hello  ", " ");
	DT_CHECK_STR("strtrim(\"  hello  \",\" \")", r, "hello");
	free(r);
}

DT_TEST(ft_strtrim, leading_trim_only, "leading trim only")
{
	char	*r;

	r = ft_strtrim("   hello", " ");
	DT_CHECK_STR("strtrim(\"   hello\",\" \")", r, "hello");
	free(r);
}

DT_TEST(ft_strtrim, trailing_trim_only, "trailing trim only")
{
	char	*r;

	r = ft_strtrim("hello   ", " ");
	DT_CHECK_STR("strtrim(\"hello   \",\" \")", r, "hello");
	free(r);
}

DT_TEST(ft_strtrim, multi_char_set, "multi-char set: internal set chars must be preserved")
{
	char	*r;

	r = ft_strtrim("abXYZba", "ab");
	DT_CHECK_STR("strtrim(\"abXYZba\",\"ab\")", r, "XYZ");
	free(r);
}

DT_TEST(ft_strtrim, no_trimming_needed, "no trimming needed")
{
	char	*r;

	r = ft_strtrim("hello", "x");
	DT_CHECK_STR("strtrim(\"hello\",\"x\")", r, "hello");
	free(r);
}

DT_TEST(ft_strtrim, empty_set_to_no_trimming, "empty set → no trimming")
{
	char	*r;

	r = ft_strtrim("hello", "");
	DT_CHECK_STR("strtrim(\"hello\",\"\")", r, "hello");
	free(r);
}

DT_TEST(ft_strtrim, empty_input, "empty input")
{
	char	*r;

	r = ft_strtrim("", " ");
	DT_CHECK_STR("strtrim(\"\",\" \")", r, "");
	free(r);
}

DT_TEST(ft_strtrim, entire_string_in_set, "entire string in set")
{
	char	*r;

	r = ft_strtrim("   ", " ");
	DT_CHECK_STR("strtrim(\"   \",\" \")", r, "");
	free(r);
}

DT_TEST(ft_strtrim, null_s1_to_null_return_without, "NULL s1 → NULL return without crash")
{
	char	*r;

	r = ft_strtrim(NULL, " ");
	if (!(r == NULL))
	{
		DT_FAILF("strtrim(NULL,\" \") → expected NULL");
		free(r);
	}
}
