import React from 'react';
import { Box, Container, Typography, Link } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

const Footer = () => {
  return (
    <Box
      component="footer"
      sx={{
        py: 3,
        px: 2,
        mt: 'auto',
        backgroundColor: (theme) => theme.palette.grey[100],
      }}
    >
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 3 }}>
          <Link component={RouterLink} to="/privacy-policy" color="inherit" underline="hover">
            Privacy Policy
          </Link>
          <Link component={RouterLink} to="/terms-of-service" color="inherit" underline="hover">
            Terms of Service
          </Link>
          <Typography color="text.secondary">
            {new Date().getFullYear()} Alexis AI. All rights reserved.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default Footer;
