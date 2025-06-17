import React from 'react';
import { Container, Typography, Box, Paper, Link } from '@mui/material';

const PrivacyPolicy = () => {
  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, my: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Privacy Policy
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Last Updated: April 22, 2025
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            1. Introduction
          </Typography>
          <Typography paragraph>
            Welcome to AI Clone ("we," "our," or "us"). We respect your privacy and are committed to protecting your personal information. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our AI Clone service.
          </Typography>
          <Typography paragraph>
            By accessing or using our service, you consent to the collection, use, and storage of your information as described in this Privacy Policy. Please read this policy carefully to understand our practices regarding your information.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            2. Information We Collect
          </Typography>
          <Typography paragraph>
            <strong>Personal Information:</strong> We collect information that you provide directly to us, including:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Account information (name, email address, password)</li>
            <li>Profile information</li>
            <li>Communication data (emails, text messages, and other communications you choose to share)</li>
            <li>Feedback and correspondence</li>
          </Typography>
          <Typography paragraph>
            <strong>Usage Information:</strong> We automatically collect certain information about your use of our service, including:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Log data (IP address, browser type, pages visited)</li>
            <li>Device information</li>
            <li>Usage patterns and preferences</li>
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            3. How We Use Your Information
          </Typography>
          <Typography paragraph>
            We use the information we collect for various purposes, including to:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Provide, maintain, and improve our services</li>
            <li>Create and train your personalized AI Clone</li>
            <li>Process and complete transactions</li>
            <li>Send you technical notices and support messages</li>
            <li>Respond to your comments and questions</li>
            <li>Develop new products and services</li>
            <li>Monitor and analyze trends, usage, and activities</li>
            <li>Detect, investigate, and prevent fraudulent or unauthorized activities</li>
            <li>Comply with legal obligations</li>
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            4. Data Sharing and Disclosure
          </Typography>
          <Typography paragraph>
            We may share your information in the following circumstances:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>With your consent or at your direction</li>
            <li>With service providers who perform services on our behalf</li>
            <li>To comply with laws or respond to legal process</li>
            <li>To protect the rights, property, and safety of our users and the public</li>
            <li>In connection with a business transfer (merger, acquisition, etc.)</li>
          </Typography>
          <Typography paragraph>
            <strong>We do not sell your personal information to third parties.</strong>
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            5. Third-Party Services
          </Typography>
          <Typography paragraph>
            Our service integrates with third-party services, including:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Google services (Gmail, OAuth)</li>
            <li>iMessage integration (through local client)</li>
            <li>Other communication platforms you choose to connect</li>
          </Typography>
          <Typography paragraph>
            When you connect these services, you authorize us to collect and store data from these platforms according to their respective privacy policies and the permissions you grant.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            6. Data Security
          </Typography>
          <Typography paragraph>
            We implement appropriate technical and organizational measures to protect your personal information against unauthorized access, accidental loss, alteration, or destruction. However, no method of electronic transmission or storage is 100% secure, and we cannot guarantee absolute security.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            7. Data Retention
          </Typography>
          <Typography paragraph>
            We retain your information for as long as necessary to provide our services and fulfill the purposes outlined in this Privacy Policy, unless a longer retention period is required by law. You can request deletion of your data at any time.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            8. Your Rights and Choices
          </Typography>
          <Typography paragraph>
            Depending on your location, you may have certain rights regarding your personal information, including:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Access to your personal information</li>
            <li>Correction of inaccurate or incomplete information</li>
            <li>Deletion of your personal information</li>
            <li>Restriction or objection to processing</li>
            <li>Data portability</li>
            <li>Withdrawal of consent</li>
          </Typography>
          <Typography paragraph>
            To exercise these rights, please contact us at support@aiclone.space.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            9. Children's Privacy
          </Typography>
          <Typography paragraph>
            Our service is not directed to children under 13, and we do not knowingly collect personal information from children under 13. If you believe we have collected information from a child under 13, please contact us.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            10. Changes to This Privacy Policy
          </Typography>
          <Typography paragraph>
            We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last Updated" date. You are advised to review this Privacy Policy periodically for any changes.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            11. Contact Us
          </Typography>
          <Typography paragraph>
            If you have any questions about this Privacy Policy, please contact us at:
          </Typography>
          <Typography paragraph>
            Email: support@aiclone.space<br />
            Website: <Link href="https://aiclone.space" target="_blank" rel="noopener noreferrer">https://aiclone.space</Link>
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
};

export default PrivacyPolicy;
