#include "get_next_line.h"

static char	*take_line(char **stash)
{
	char	*nl = gnl_strchr(*stash, '\n');
	size_t	len = nl ? (size_t)(nl - *stash) + 1 : gnl_strlen(*stash);
	char	*line = gnl_join(NULL, *stash, len);
	char	*rest;

	if (!line)
		return (free(*stash), *stash = NULL, NULL);
	rest = NULL;
	if ((*stash)[len])
	{
		rest = gnl_join(NULL, *stash + len, gnl_strlen(*stash + len));
		if (!rest)
			return (free(line), free(*stash), *stash = NULL, NULL);
	}
	free(*stash);
	*stash = rest;
	return (line);
}

char	*get_next_line(int fd)
{
	static char	*stash;
	char		*buf;
	ssize_t		n;

	if (fd < 0 || BUFFER_SIZE <= 0 || read(fd, NULL, 0) < 0)
		return (free(stash), stash = NULL, NULL);
	buf = malloc((size_t)BUFFER_SIZE + 1);
	if (!buf)
		return (free(stash), stash = NULL, NULL);
	n = 1;
	while (!gnl_strchr(stash, '\n') && n > 0)
	{
		n = read(fd, buf, BUFFER_SIZE);
		if (n < 0)
			return (free(buf), free(stash), stash = NULL, NULL);
		if (n > 0)
		{
			stash = gnl_join(stash, buf, (size_t)n);
			if (!stash)
				return (free(buf), NULL);
		}
	}
	free(buf);
	if (!stash || !*stash)
		return (free(stash), stash = NULL, NULL);
	return (take_line(&stash));
}
