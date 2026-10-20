#include "memcheck.h"

static void	*call(void)
{
	return (ft_strtrim("  hello  ", " "));
}

DT_TEST(memory, ft_strtrim, "ft_strtrim: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_strtrim", call, release_plain);
}
