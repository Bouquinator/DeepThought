#include "libft_test.h"

DT_TEST(ft_toupper, all_chars, "Same result as toupper() for every value from -1 to 255")
{
	for (int c = -1; c <= 255; c++)
		if (ft_toupper(c) != toupper(c))
		{
			dt_note("first difference for c = %d", c);
			DT_EXPECT_EQ_INT(ft_toupper(c), toupper(c));
			return ;
		}
}
