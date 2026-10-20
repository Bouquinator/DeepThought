#include "pf.h"
/* Bonus part 2: '#', ' ' and '+'. */

DT_TEST(bonus_hash_space_plus, hash, "'#': 0x / 0X prefix for non-zero hexadecimal values")
{
	/* no prefix for 0 */
	PF("%#x", 0u);
	PF("%#x", 0xbeefu);
	PF("%#X", 0xbeefu);
	PF("%#10x", 0xffu);
	PF("%#-10x|", 0xffu);
	/* zeros go between the prefix and the digits */
	PF("%#010x", 0xffu);
	PF("%#.5x", 1u);
	PF("%#.0x", 0u);
	PF("%#08.3x", 0xau);
}

DT_TEST(bonus_hash_space_plus, space, "' ': a space before positive signed numbers")
{
	PF("% d", 42);
	PF("% d", -42);
	PF("% d", 0);
	PF("% 5d", 42);
	PF("% -5d|", 42);
	PF("% 05d", 42);
	PF("% .3d", 7);
	PF("% .0d", 0);
}

DT_TEST(bonus_hash_space_plus, plus, "'+': always print the sign, and '+' overrides ' '")
{
	PF("%+d", 42);
	PF("%+d", -42);
	PF("%+d", 0);
	PF("%+5d", 42);
	PF("%+-5d|", 42);
	PF("%+05d", 42);
	PF("%+.3d", 7);
	PF("%+.0d", 0);
	/* '+' wins over ' ', whatever the order */
	PF("%+ d", 42);
	PF("% +d", 42);
}

