#include "pf.h"
/*
** Flags, width and precision must not leak into the next conversion/call.
** Each flag on its own is covered by bonus_minus_zero_dot and
** bonus_hash_space_plus.
*/

DT_TEST(bonus_combinations, cases, "flags, width and precision must not leak into the next conversion or call")
{
	PF("%-10d|", 1);
	PF("%d|", 2);
	PF("%08.3d", 3);
	PF("%d", 4);
	PF("%#x", 5u);
	PF("%x", 5u);
	PF("%+d", 6);
	PF("%d", 6);
	PF("%.2s", "eight");
	PF("%s", "eight");
	PF("%-5d|%d|%05d|%d|%#x|%x|%+d|%d|%.1s|%s", 1, 2, 3, 4, 5u, 6u,
		7, 8, "nine", "ten");
}
