#include "sstyle.h"
#include <stdlib.h>
#include <string.h>

DT_TEST(ft_calloc, 5_ints, "5 ints")
{
	void	*ptr;
	char	zeros[64];

	memset(zeros, 0, sizeof(zeros));

	ptr = ft_calloc(5, sizeof(int));
	DT_CHECK_NOT_NULL("calloc(5, int) non-NULL", ptr);
	if (ptr)
	{
		DT_CHECK_MEM("calloc(5, int) all zeros", ptr, zeros, 5 * sizeof(int));
		free(ptr);
	}
}

DT_TEST(ft_calloc, large_allocation, "large allocation: 100 000 bytes, first 64 must be zero")
{
	void	*ptr;
	char	zeros[64];

	memset(zeros, 0, sizeof(zeros));

	ptr = ft_calloc(100000, 1);
	DT_CHECK_NOT_NULL("calloc(100000, 1) non-NULL", ptr);
	if (ptr)
	{
		DT_CHECK_MEM("calloc(100000,1) first 64 bytes zero", ptr, zeros, sizeof(zeros));
		free(ptr);
	}
}

DT_TEST(ft_calloc, calloc_0_x, "calloc(0, x): implementation-defined; just must not crash")
{
	void	*ptr;

	ptr = ft_calloc(0, 4);
	if (ptr)
		free(ptr);
}

DT_TEST(ft_calloc, overflow_safe, "overflow-safe: SIZE_MAX * 2 overflows; must not crash")
{
	{
		void	*p = ft_calloc((size_t)-1, 2);
		if (p)
			free(p);
	}
}
