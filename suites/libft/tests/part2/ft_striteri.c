#include "libft_test.h"

static void	up_even(unsigned int i, char *c)
{
	if (i % 2 == 0)
		*c = (char)toupper(*c);
}

DT_TEST(ft_striteri, basic, "Calls f(index, &char) in place")
{
	char	s[] = "abcdef";

	ft_striteri(s, up_even);
	DT_EXPECT_EQ_STR(s, "AbCdEf");
}
