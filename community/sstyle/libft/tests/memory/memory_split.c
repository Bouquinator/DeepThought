#include "memcheck.h"

static void	*call(void)
{
	return (ft_split("  one two  three four ", ' '));
}

DT_TEST(memory, ft_split, "ft_split: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_split", call, release_split);
}
