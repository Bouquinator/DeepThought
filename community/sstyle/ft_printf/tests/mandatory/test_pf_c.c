#include "pf.h"
DT_TEST(printf_c, basic, "printf_c: basic cases")
{
	PF("%c", 'a');
	PF("%c", '%');
}

DT_TEST(printf_c, nul_is_written_and_counted, "NUL is written and counted")
{
	PF("%c", '\0');
	PF("a%cb", '\0');
}

DT_TEST(printf_c, int_argument_converted_to_unsigned_char, "int argument converted to unsigned char")
{
	PF("%c", 128);
	PF("%c", 255);
	PF("%c", -1);
	PF("%c", 256 + 'A');
}
