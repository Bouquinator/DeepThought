#include "libft_test.h"

DT_TEST(ft_isascii, all_chars, "Same truthiness as isascii() for every value from -1 (EOF) to 255")
{
	for (int c = -1; c <= 255; c++)
		if (!!ft_isascii(c) != !!isascii(c))
		{
			dt_note("first difference for c = %d", c);
			DT_EXPECT_EQ_INT(!!ft_isascii(c), !!isascii(c));
			return ;
		}
}
