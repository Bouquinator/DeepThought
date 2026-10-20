#include "pf_project.h"

DT_TEST(printf_project, files, "libftprintf.a at the root, ft_printf.h with the prototype")
{
	check_files();
}

DT_TEST(printf_project, makefile, "Makefile: NAME, all, clean, fclean, re, ar (not libtool), -Wall -Wextra -Werror")
{
	check_makefile();
}

#ifndef _WIN32

DT_TEST(printf_project, no_relink, "running make (and make all) twice does not relink")
{
	check_relink("");
	check_relink("all");
}

DT_TEST(printf_project, external_functions, "only malloc, free, write (and va_*) as external functions")
{
	check_external_functions();
}

#endif
