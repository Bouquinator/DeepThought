#include "printf_test.h"

DT_TEST(width, numbers, "Minimum field width on numbers")
{
	CMP("[%5d]", 42);
	CMP("[%5d]", -42);
	CMP("[%1d]", 12345);
	CMP("[%10u]", 42u);
	CMP("[%8x]", 255);
}

DT_TEST(width, strings_chars, "Width on %s, %c and %p")
{
	CMP("[%10s]", "abc");
	CMP("[%5c]", 'z');
	CMP("[%20p]", (void *)0x1234);
}

DT_TEST(minus, left_align, "'-' left-aligns in the field")
{
	CMP("[%-5d]", 42);
	CMP("[%-10s]", "abc");
	CMP("[%-5c]", 'z');
	CMP("[%-8x]", 255);
	CMP("[%-20p]", (void *)0x1234);
}

DT_TEST(zero, padding, "'0' pads numbers with zeros")
{
	CMP("[%05d]", 42);
	CMP("[%05d]", -42);
	CMP("[%08X]", 0xABC);
	CMP("[%05u]", 7u);
}

DT_TEST(zero, minus_wins, "'-' overrides '0'")
{
	CMP("[%-05d]", 42);
}
