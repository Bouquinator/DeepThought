#include "memcheck.h"

static void	*call(void)
{
	return (ft_substr("Hello, World", 7, 5));
}

DT_TEST(memory, ft_substr, "ft_substr: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_substr", call, release_plain);
}
