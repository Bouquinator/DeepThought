#include "printf_test.h"

DT_TEST(x, lower, "%x prints lowercase hexadecimal")
{
	CMP("%x", 255);
	CMP("%x", 0);
	CMP("%x", 0xdeadbeef);
}

DT_TEST(x, upper, "%X prints uppercase hexadecimal")
{
	CMP("%X", 255);
	CMP("%X", 0xDEADBEEF);
}

DT_TEST(x, limits, "UINT_MAX and negative values")
{
	CMP("%x", UINT_MAX);
	CMP("%X", -1);
	CMP("%x", INT_MIN);
}
