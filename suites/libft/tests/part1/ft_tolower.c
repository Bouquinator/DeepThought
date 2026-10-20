#include "libft_test.h"

DT_TEST(ft_tolower, all_chars, "Same result as tolower() for every value from -1 to 255")
{
	for (int c = -1; c <= 255; c++)
		if (ft_tolower(c) != tolower(c))
		{
			dt_note("first difference for c = %d", c);
			DT_EXPECT_EQ_INT(ft_tolower(c), tolower(c));
			return ;
		}
}
