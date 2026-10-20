#include "pf.h"
/* Bonus part 1: '-', '0', '.' and minimum field width. */

DT_TEST(bonus_minus_zero_dot, width_only, "minimum field width alone")
{
	PF("%5d", 42);
	PF("%5d", -42);
	/* width smaller than the output */
	PF("%1d", 42);
	PF("%5u", 42u);
	PF("%8x", 0xbeefu);
	PF("%5s", "abc");
	PF("%10s", (char *)NULL);
	PF("%3c", 'a');
	PF("%3c", '\0');
	PF("%20p", (void *)0xdeadbeef);
	PF("%10p", NULL);
	PF("%100000c", 'w');
}

DT_TEST(bonus_minus_zero_dot, minus, "'-': left-justify in the field")
{
	PF("%-5d|", 42);
	PF("%-5d|", -42);
	PF("%-5u|", 42u);
	PF("%-8x|", 0xbeefu);
	PF("%-5s|", "abc");
	PF("%-10s|", (char *)NULL);
	PF("%-3c|", 'a');
	PF("%-3c|", '\0');
	PF("%-20p|", (void *)0xdeadbeef);
	/* repeated flag, flag without width */
	PF("%---5d|", 7);
	PF("%-d|", 7);
}

DT_TEST(bonus_minus_zero_dot, zero, "'0': pad numbers with zeros ('-' and a precision disable it)")
{
	PF("%05d", 42);
	/* sign goes before the zeros */
	PF("%05d", -42);
	PF("%05u", 42u);
	PF("%08x", 0xbeefu);
	PF("%0d", 5);
	/* '-' wins over '0', whatever the order */
	PF("%-05d|", 42);
	PF("%0-5d|", -42);
	/* a precision disables '0' for integers */
	PF("%08.3d", 42);
	PF("%08.3d", -42);
	PF("%08.0d", 0);
}

DT_TEST(bonus_minus_zero_dot, precision, "'.': precision for numbers and strings")
{
	/* precision 0 with value 0 prints nothing */
	PF("%.0d", 0);
	PF("%.d", 0);
	PF("%.0d", 1);
	PF("%.3d", 7);
	PF("%.3d", -7);
	PF("%.3d", 12345);
	PF("%.1000d", -1);
	PF("%.0u", 0u);
	PF("%.5u", 42u);
	PF("%.0x", 0u);
	PF("%.4x", 0xfu);
	/* width + precision */
	PF("%8.3d", 42);
	PF("%8.3d", -42);
	PF("%-8.3d|", -42);
	PF("%3.8d", 42);
	PF("%5.0d", 0);
	PF("%10.5x", 0xabcu);
	/* strings */
	PF("%.0s", "hello");
	PF("%.3s", "hello");
	PF("%.10s", "hello");
	PF("%10.3s|", "hello");
	PF("%-10.3s|", "hello");
	/* NULL string with precision (glibc: "" when precision < 6) */
	PF("%.5s", (char *)NULL);
	PF("%.6s", (char *)NULL);
}

