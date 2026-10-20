#include "pf.h"
static void	spec_values(const char *fmt)
{
	PF_L(fmt, fmt, 0);
	PF_L(fmt, fmt, 9);
	PF_L(fmt, fmt, 10);
	PF_L(fmt, fmt, -1);
	PF_L(fmt, fmt, -10);
	PF_L(fmt, fmt, INT_MAX);
	PF_L(fmt, fmt, INT_MIN);
}

DT_TEST(printf_di, d, "%d")
{
	spec_values("%d");
}

DT_TEST(printf_di, i, "%i")
{
	spec_values("%i");
}
