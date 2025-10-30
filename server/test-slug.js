const slugify = require('slugify');

const slug = (text) => slugify(text, { lower: true, strict: true });

console.log(slug('Hello World!')); // prints 'hello-world'