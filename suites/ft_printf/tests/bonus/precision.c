#include "printf_test.h"

DT_TEST(precision, numbers, "Precision gives the minimum number of digits")
{
	CMP("[%.5d]", 42);
	CMP("[%.5d]", -42);
	CMP("[%.3x]", 10);
	CMP("[%.10u]", 123u);
}

DT_TEST(precision, zero_value, "%.0d with 0 prints nothing")
{
	CMP("[%.0d]", 0);
	CMP("[%.d]", 0);
	CMP("[%5.0d]", 0);
	CMP("[%.0x]", 0);
}

DT_TEST(precision, strings, "Precision truncates strings")
{
	CMP("[%.3s]", "abcdef");
	CMP("[%.0s]", "abc");
	CMP("[%.10s]", "abc");
	CMP("[%.s]", "abc");
}

DT_TEST(precision, with_width, "Width and precision together")
{
	CMP("[%8.3d]", 42);
	CMP("[%-8.3d]", -42);
	CMP("[%8.3s]", "abcdef");
}

DT_TEST(precision, zero_ignored, "'0' is ignored when a precision is given")
{
	CMP("[%08.3d]", 42);
	CMP("[%08.3x]", 255);
}
