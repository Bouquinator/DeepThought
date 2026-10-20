/* A tiny 'student' echo with -n support — and one bug (no space handling for empty args). */
#include <string.h>
#include <unistd.h>

int	main(int argc, char **argv)
{
	int	i = 1;
	int	newline = 1;

	if (argc > 1 && strcmp(argv[1], "-n") == 0)
	{
		newline = 0;
		i++;
	}
	while (i < argc)
	{
		write(1, argv[i], strlen(argv[i]));
		if (i + 1 < argc && argv[i][0])
			write(1, " ", 1);
		i++;
	}
	if (newline)
		write(1, "\n", 1);
	return (0);
}
