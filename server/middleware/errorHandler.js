const errorHandler = (err, _req, res, _next) => {
  const status  = err.status  || 500;
  const message = err.message || 'Internal server error';

  console.error(`[${status}] ${message}`, err.detail || '');

  res.status(status).json({
    error:   message,
    ...(process.env.NODE_ENV === 'development' && {
      detail: err.detail,
      stack:  err.stack
    })
  });
};

export default errorHandler;