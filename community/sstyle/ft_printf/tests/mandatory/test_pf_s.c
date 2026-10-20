#include "pf.h"
DT_TEST(printf_s, basic, "printf_s: basic cases")
{
	PF("%s", "hello");
	PF("%s", "");
}

DT_TEST(printf_s, conversion_characters_in_the_argument, "conversion characters inside the argument are not interpreted")
{
	PF("%s", "%d %s %%");
	PF("%s", "\x01\x7f\xff");
}

DT_TEST(printf_s, null_string_glibc_prints_null, "NULL string (glibc prints \"(null)\")")
{
	char		*null_str;

	null_str = NULL;
	PF("%s", null_str);
	PF("%s %s", null_str, "after");
}

DT_TEST(printf_s, very_long_argument, "very long argument")
{
	static char	big[100001];

	memset(big, 'x', sizeof(big) - 1);
	big[sizeof(big) - 1] = '\0';
	PF_L("\"%s\", <100000 x>", "%s", big);
}
