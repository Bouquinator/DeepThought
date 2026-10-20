#include "memcheck.h"

static void	*call(void)
{
	return (ft_calloc(4, 8));
}

DT_TEST(memory, ft_calloc, "ft_calloc: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_calloc", call, release_plain);
}
