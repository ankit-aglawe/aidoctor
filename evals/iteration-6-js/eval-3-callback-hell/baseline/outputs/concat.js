const fs = require('fs');

fs.readFile('a.txt', 'utf8', (errA, dataA) => {
  if (errA) {
    console.error('Error reading a.txt:', errA);
    return;
  }
  fs.readFile('b.txt', 'utf8', (errB, dataB) => {
    if (errB) {
      console.error('Error reading b.txt:', errB);
      return;
    }
    fs.readFile('c.txt', 'utf8', (errC, dataC) => {
      if (errC) {
        console.error('Error reading c.txt:', errC);
        return;
      }
      const combined = dataA + dataB + dataC;
      fs.writeFile('out.txt', combined, (errW) => {
        if (errW) {
          console.error('Error writing out.txt:', errW);
          return;
        }
        console.log('Successfully wrote out.txt');
      });
    });
  });
});
