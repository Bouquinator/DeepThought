#include "libft_test.h"

DT_TEST(ft_isdigit, all_chars, "Same truthiness as isdigit() for every value from -1 (EOF) to 255")
{
	for (int c = -1; c <= 255; c++)
		if (!!ft_isdigit(c) != !!isdigit(c))
		{
			dt_note("first difference for c = %d", c);
			DT_EXPECT_EQ_INT(!!ft_isdigit(c), !!isdigit(c));
			return ;
		}
}
