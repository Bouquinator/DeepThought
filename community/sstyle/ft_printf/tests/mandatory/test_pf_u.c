#include "pf.h"
DT_TEST(printf_u, basic, "printf_u: basic cases")
{
	PF("%u", 0u);
	PF("%u", 9u);
	PF("%u", 10u);
	PF("%u", (unsigned int)INT_MAX + 1u);
	PF("%u", UINT_MAX);
}

DT_TEST(printf_u, negative_ints_reinterpreted_as_unsigned, "negative ints reinterpreted as unsigned")
{
	PF("%u", -1);
}
