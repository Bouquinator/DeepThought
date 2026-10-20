#include "../memory/memcheck.h"

static void	*call(void)
{
	return (ft_lstnew(NULL));
}

DT_TEST(memory, ft_lstnew, "ft_lstnew: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_lstnew", call, release_plain);
}
