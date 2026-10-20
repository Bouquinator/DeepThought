#include "pf.h"
static void	spec_values(const char *fmt)
{
	PF_L(fmt, fmt, 0u);
	PF_L(fmt, fmt, 9u);
	PF_L(fmt, fmt, 10u);
	PF_L(fmt, fmt, 15u);
	PF_L(fmt, fmt, 16u);
	PF_L(fmt, fmt, 0xabcdefu);
	PF_L(fmt, fmt, UINT_MAX);
	PF_L(fmt, fmt, INT_MIN);
}

DT_TEST(printf_x, x, "%x")
{
	spec_values("%x");
}

DT_TEST(printf_x, upper_x, "%X")
{
	spec_values("%X");
}
