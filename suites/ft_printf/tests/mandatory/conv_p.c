#include "printf_test.h"

DT_TEST(p, basic, "%p prints an address in hexadecimal with 0x")
{
	int	x;

	CMP("%p", (void *)&x);
	CMP("%p", (void *)0x2a);
}

DT_TEST(p, null, "%p with NULL behaves like printf on this system")
{
	CMP("%p", NULL);
	CMP("[%p]", (void *)0);
}

DT_TEST(p, extremes, "Largest addresses (ULONG_MAX, LONG_MIN)")
{
	CMP("%p", (void *)ULONG_MAX);
	CMP("%p", (void *)LONG_MIN);
	CMP("%p %p", (void *)LONG_MAX, (void *)-1);
}
