#include "memcheck.h"

static char	map_upper(unsigned int i, char c)
{
	(void)i;
	if (c >= 'a' && c <= 'z')
		return (c - 32);
	return (c);
}

static void	*call(void)
{
	return (ft_strmapi("abc", map_upper));
}

DT_TEST(memory, ft_strmapi, "ft_strmapi: no leak, and returns NULL without leaking when any of its mallocs fails")
{
	check_case("ft_strmapi", call, release_plain);
}
