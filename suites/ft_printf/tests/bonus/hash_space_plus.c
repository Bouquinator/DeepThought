#include "printf_test.h"

DT_TEST(hash, hex_prefix, "'#' adds 0x / 0X to non-zero hex values")
{
	CMP("%#x", 255);
	CMP("%#X", 255);
	CMP("%#x", 0);
	CMP("[%#10x]", 42);
	CMP("[%#-10X]", 42);
}

DT_TEST(plus, sign, "'+' always prints the sign")
{
	CMP("%+d", 42);
	CMP("%+d", -42);
	CMP("%+i", 0);
	CMP("[%+5d]", 7);
}

DT_TEST(space, sign, "' ' puts a space before positive numbers")
{
	CMP("% d", 42);
	CMP("% d", -42);
	CMP("% i", 0);
}

DT_TEST(plus, wins_over_space, "'+' overrides ' '")
{
	CMP("%+ d", 42);
	CMP("% +d", 42);
}
