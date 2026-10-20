#include "printf_test.h"

DT_TEST(u, basic, "%u prints an unsigned decimal")
{
	CMP("%u", 42u);
	CMP("%u", 0u);
}

DT_TEST(u, limits, "UINT_MAX")
{
	CMP("%u", UINT_MAX);
}

DT_TEST(u, negative, "A negative int printed with %u wraps around")
{
	CMP("%u", -1);
	CMP("%u", INT_MIN);
}
