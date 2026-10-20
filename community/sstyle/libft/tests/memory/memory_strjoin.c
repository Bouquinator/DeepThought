#include "memcheck.h"

static void	*call(void)
{
	return (ft_strjoin("foo", "bar"));
}

DT_TEST(memory, ft_strjoin, "ft_strjoin: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_strjoin", call, release_plain);
}
