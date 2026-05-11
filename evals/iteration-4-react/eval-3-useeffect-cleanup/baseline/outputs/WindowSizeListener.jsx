import { useState, useEffect } from 'react';

export default function WindowSizeListener() {
  const [width, setWidth] = useState(window.innerWidth);

  useEffect(() => {
    const handleResize = () => {
      setWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
  }, []);

  return (
    <div>
      <p>Current window width: {width}px</p>
    </div>
  );
}
