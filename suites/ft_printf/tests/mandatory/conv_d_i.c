#include "printf_test.h"

DT_TEST(d, basic, "%d prints a signed decimal")
{
	CMP("%d", 42);
	CMP("%d", -42);
	CMP("%d", 0);
}

DT_TEST(d, limits, "INT_MAX and INT_MIN")
{
	CMP("%d", INT_MAX);
	CMP("%d", INT_MIN);
}

DT_TEST(d, several, "Several numbers")
{
	CMP("%d %d %d %d", 1, -10, 100, -1000);
}

DT_TEST(i, basic, "%i behaves like %d")
{
	CMP("%i", 42);
	CMP("%i", -2147483647 - 1);
	CMP("%i%i", 0, -0);
}
