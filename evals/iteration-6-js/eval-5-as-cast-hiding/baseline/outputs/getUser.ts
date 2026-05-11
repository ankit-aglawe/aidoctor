interface User {
  id: string;
  name: string;
  email: string;
}

function getUser(rawJson: string): User {
  const parsed = JSON.parse(rawJson) as User;
  return parsed;
}

export { getUser, User };
