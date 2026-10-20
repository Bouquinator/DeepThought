#include "pf_project.h"

DT_TEST(bonus_project, bonus_rule, "the Makefile has a 'bonus' rule")
{
	char	*mk;

	mk = read_file("Makefile");
	pass_fail("Makefile has a 'bonus' rule (42 rules)",
		mk && mk_has_target(mk, "bonus"), NULL);
	free(mk);
}

#ifndef _WIN32

DT_TEST(bonus_project, no_relink, "running make bonus twice does not relink")
{
	check_relink("bonus");
}

#endif
