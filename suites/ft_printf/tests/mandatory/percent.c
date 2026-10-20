#include "printf_test.h"

DT_TEST(percent, alone, "%% prints a single %")
{
	CMP("%%");
}

DT_TEST(percent, in_text, "%% inside text and next to conversions")
{
	CMP("100%%");
	CMP("%%%d%%", 42);
	CMP("%%%%");
}
