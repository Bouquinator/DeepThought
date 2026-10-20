#include "libft_test.h"

static void	check(const char *h, const char *n, size_t len)
{
	dt_input("big=\"%s\", little=\"%s\", len=%zu", h, n, len);
	DT_EXPECT_EQ_PTR(ft_strnstr(h, n, len), ref_strnstr(h, n, len));
}

DT_TEST(ft_strnstr, found, "Finds the needle")
{
	check("lorem ipsum dolor", "ipsum", 17);
}

DT_TEST(ft_strnstr, empty_needle, "Empty needle returns the haystack")
{
	check("lorem", "", 3);
}

DT_TEST(ft_strnstr, beyond_len, "A match that ends after len is not found")
{
	check("lorem ipsum", "ipsum", 8);
}

DT_TEST(ft_strnstr, exact_len, "A match ending exactly at len is found")
{
	check("lorem ipsum", "ipsum", 11);
}

DT_TEST(ft_strnstr, not_found, "Absent needle")
{
	check("aaaaab", "aab", 4);
	check("aaaaab", "aab", 6);
}
