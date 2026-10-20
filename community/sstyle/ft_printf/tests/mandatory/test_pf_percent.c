#include "pf.h"
DT_TEST(printf_percent, cases, "%%, consecutive %%, %% before text and before a conversion")
{
	PF("%%");
	PF("%%%%");
	PF("%%d");
	PF("%%%d", 42);
}
