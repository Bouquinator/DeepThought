#include "memcheck.h"

static void	*call(void)
{
	return (ft_itoa(-2147483647 - 1));
}

DT_TEST(memory, ft_itoa, "ft_itoa: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_itoa", call, release_plain);
}
