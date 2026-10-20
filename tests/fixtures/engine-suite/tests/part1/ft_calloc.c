#include "libft_test.h"

DT_TEST(ft_calloc, zeroed, "Memory is zeroed")
{
	unsigned char	*p = ft_calloc(10, sizeof(int));
	unsigned char	z[10 * sizeof(int)] = {0};

	DT_ASSERT_NOT_NULL(p);
	DT_EXPECT_EQ_MEM(p, z, sizeof(z));
	DT_EXPECT_ALLOC_SIZE(p, 10 * sizeof(int));
	free(p);
}

DT_TEST(ft_calloc, zero_size, "calloc(0, 0) returns a pointer that can be freed")
{
	void	*p = ft_calloc(0, 0);

	free(p);
}

DT_TEST(ft_calloc, overflow, "nmemb * size overflowing size_t returns NULL")
{
	void	*p = ft_calloc(SIZE_MAX / 2 + 2, 2);

	DT_EXPECT_NULL(p);
	free(p);
}

DT_TEST(ft_calloc, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(ft_calloc(4, 4));
}
