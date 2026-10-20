#include "pf.h"
DT_TEST(printf_p, null, "NULL: Linux/glibc prints \"(nil)\", macOS prints \"0x0\" — both accepted")
{
	PF_L_ALT("\"%p\", NULL", "(nil)", "%p", NULL);

	PF("%p", (void *)1);
	PF("%p", (void *)15);
	PF("%p", (void *)16);
	PF("%p", (void *)0xabcdef);
	PF("%p", (void *)0x100000000);
	PF("%p", (void *)LONG_MIN);
	PF("%p", (void *)ULONG_MAX);
}

DT_TEST(printf_p, real_address, "real address")
{
	int		local;

	PF("%p", (void *)&local);
}
