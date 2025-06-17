import React from 'react';
import { Container, Typography, Box, Paper, Link } from '@mui/material';

const TermsOfService = () => {
  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, my: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Terms of Service
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Last Updated: April 22, 2025
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            1. Acceptance of Terms
          </Typography>
          <Typography paragraph>
            Welcome to AI Clone. By accessing or using our website, mobile applications, or any other services provided by AI Clone (collectively, the "Service"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, please do not use our Service.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            2. Description of Service
          </Typography>
          <Typography paragraph>
            AI Clone provides a personalized artificial intelligence service that learns from your communication data to create a digital clone that can respond to messages in your style. Our Service may include features such as:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Creating and training a personalized AI clone</li>
            <li>Auto-responding to messages and emails</li>
            <li>Integration with third-party communication platforms</li>
            <li>Data analysis and processing</li>
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            3. User Accounts
          </Typography>
          <Typography paragraph>
            To use certain features of our Service, you must create an account. You are responsible for maintaining the confidentiality of your account information and for all activities that occur under your account. You agree to:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Provide accurate and complete information when creating your account</li>
            <li>Update your information to keep it accurate and current</li>
            <li>Notify us immediately of any unauthorized use of your account</li>
            <li>Be responsible for all activities that occur under your account</li>
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            4. User Content and Data
          </Typography>
          <Typography paragraph>
            Our Service requires access to your communication data to create and train your AI clone. By using our Service, you grant us permission to:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Access, collect, and process your communication data</li>
            <li>Use your data to train and improve your AI clone</li>
            <li>Store your data on our secure servers</li>
            <li>Generate responses on your behalf when authorized</li>
          </Typography>
          <Typography paragraph>
            You retain all ownership rights to your content. We will only use your data as described in our Privacy Policy and as necessary to provide and improve our Service.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            5. Acceptable Use
          </Typography>
          <Typography paragraph>
            You agree not to use our Service to:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Violate any applicable laws or regulations</li>
            <li>Infringe on the rights of others</li>
            <li>Send spam, unsolicited messages, or advertisements</li>
            <li>Distribute malware or other harmful code</li>
            <li>Impersonate others or provide false information</li>
            <li>Interfere with the proper functioning of the Service</li>
            <li>Attempt to gain unauthorized access to the Service or related systems</li>
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            6. Third-Party Services and Integrations
          </Typography>
          <Typography paragraph>
            Our Service may integrate with third-party services (such as Gmail, iMessage, etc.). Your use of these integrations is subject to the respective third-party terms and privacy policies. We are not responsible for the practices of these third parties.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            7. Intellectual Property
          </Typography>
          <Typography paragraph>
            All content, features, and functionality of our Service, including but not limited to text, graphics, logos, icons, images, audio clips, digital downloads, data compilations, and software, are the exclusive property of AI Clone or its licensors and are protected by copyright, trademark, and other intellectual property laws.
          </Typography>
          <Typography paragraph>
            We grant you a limited, non-exclusive, non-transferable, and revocable license to use our Service for personal, non-commercial purposes in accordance with these Terms.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            8. Disclaimer of Warranties
          </Typography>
          <Typography paragraph>
            OUR SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT ANY WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. TO THE FULLEST EXTENT PERMITTED BY LAW, WE DISCLAIM ALL WARRANTIES, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
          </Typography>
          <Typography paragraph>
            We do not guarantee that our Service will be uninterrupted, timely, secure, or error-free, or that any content generated by your AI clone will be accurate, appropriate, or meet your expectations.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            9. Limitation of Liability
          </Typography>
          <Typography paragraph>
            TO THE FULLEST EXTENT PERMITTED BY LAW, IN NO EVENT SHALL AI CLONE, ITS AFFILIATES, OR THEIR RESPECTIVE OFFICERS, DIRECTORS, EMPLOYEES, OR AGENTS BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, USE, OR GOODWILL, ARISING OUT OF OR IN CONNECTION WITH YOUR USE OF OUR SERVICE.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            10. Indemnification
          </Typography>
          <Typography paragraph>
            You agree to indemnify, defend, and hold harmless AI Clone, its affiliates, and their respective officers, directors, employees, and agents from and against any claims, liabilities, damages, losses, costs, expenses, or fees (including reasonable attorneys' fees) arising from:
          </Typography>
          <Typography component="ul" sx={{ pl: 4 }}>
            <li>Your use of our Service</li>
            <li>Your violation of these Terms</li>
            <li>Your violation of any rights of another person or entity</li>
            <li>Any content generated by your AI clone when authorized by you</li>
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            11. Termination
          </Typography>
          <Typography paragraph>
            We may terminate or suspend your account and access to our Service at any time, without prior notice or liability, for any reason, including but not limited to a breach of these Terms.
          </Typography>
          <Typography paragraph>
            You may terminate your account at any time by contacting us. Upon termination, your right to use the Service will immediately cease.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            12. Changes to Terms
          </Typography>
          <Typography paragraph>
            We may modify these Terms at any time by posting the revised Terms on our website. Your continued use of our Service after any such changes constitutes your acceptance of the new Terms.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            13. Governing Law
          </Typography>
          <Typography paragraph>
            These Terms shall be governed by and construed in accordance with the laws of the State of California, without regard to its conflict of law provisions.
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            14. Contact Information
          </Typography>
          <Typography paragraph>
            If you have any questions about these Terms, please contact us at:
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

export default TermsOfService;
