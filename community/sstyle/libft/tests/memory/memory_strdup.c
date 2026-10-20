#include "memcheck.h"

static void	*call(void)
{
	return (ft_strdup("hello"));
}

DT_TEST(memory, ft_strdup, "ft_strdup: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_strdup", call, release_plain);
}
