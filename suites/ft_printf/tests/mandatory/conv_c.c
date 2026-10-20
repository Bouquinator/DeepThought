#include "printf_test.h"

DT_TEST(c, basic, "%c prints one character")
{
	CMP("%c", 'a');
	CMP("[%c]", '0');
}

DT_TEST(c, several, "Several %c in a row and around text")
{
	CMP("%c%c%c", 'a', 'b', 'c');
	CMP("x%cy%cz", '-', '+');
}

DT_TEST(c, nul_char, "%c with '\\0' writes a NUL byte and counts it")
{
	CMP("%c", '\0');
	CMP("a%cb", '\0');
}

DT_TEST(c, non_printable, "Non-printable and high characters")
{
	CMP("%c%c%c", '\t', '\n', 127);
	CMP("%c", 200);
}
