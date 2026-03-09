import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace block 1 & 2 & 3 (All instances of Login/Auth OTP)
auth_otp_html = f'''\\n\\nBest regards,\\nThe SkillVerify Team'
        msg_email.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4f46e5; text-align: center;">SkillVerify Verification</h2>
            <p>Hello,</p>
            <p>Your verification code is:</p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 24px; font-weight: bold; padding: 10px 20px; background-color: #f3f4f6; border-radius: 5px; letter-spacing: 2px;">{{otp}}</span>
            </div>
            <p>Please enter this code to complete your login securely. This code is valid for a limited time.</p>
            <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
            <p style="font-size: 12px; color: #777;">If you did not request this code, please securely ignore this email.</p>
            <p style="font-size: 12px; color: #777;">Best regards,<br><strong>The SkillVerify Team</strong></p>
        </div>
        """'''

block1_old = """                msg_email.body = f'Your verification code is: {otp}\\n\\nPlease enter this code to complete your login.'"""
block1_new = f"""                msg_email.body = f'Your verification code is: {{otp}}\\n\\nPlease enter this code to complete your login.{auth_otp_html}"""
content = content.replace(block1_old, block1_new)

# Registration OTP
reg_otp_html = f'''\\n\\nBest regards,\\nThe SkillVerify Team'
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4f46e5; text-align: center;">Welcome to SkillVerify!</h2>
            <p>Hello,</p>
            <p>Thank you for registering. Your verification code is:</p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 24px; font-weight: bold; padding: 10px 20px; background-color: #f3f4f6; border-radius: 5px; letter-spacing: 2px;">{{otp}}</span>
            </div>
            <p>Please enter this code to complete your registration securely.</p>
            <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
            <p style="font-size: 12px; color: #777;">Best regards,<br><strong>The SkillVerify Team</strong></p>
        </div>
        """'''

block2_old = """        msg.body = f'Your verification code is: {otp}\\n\\nPlease enter this code to complete your registration.'"""
block2_new = f"""        msg.body = f'Your verification code is: {{otp}}\\n\\nPlease enter this code to complete your registration.{reg_otp_html}"""
content = content.replace(block2_old, block2_new)


# Login OTP
block3_old = """        msg.body = f'Your verification code is: {otp}\\n\\nPlease enter this code to complete your login.'"""
block3_new = f"""        msg.body = f'Your verification code is: {{otp}}\\n\\nPlease enter this code to complete your login.{auth_otp_html.replace('msg_email', 'msg')}"""
content = content.replace(block3_old, block3_new)


# Replace block 4 (Demo Host)
block4_old = """        msg.body = f"A new demo has been scheduled!\\n\\nDate: {date}\\nTime: {time}\\nCustomer Email: {customer_email}\\n\\nPlease follow up."
        mail.send(msg)"""
block4_new = """        msg.body = f"A new demo has been scheduled!\\n\\nDate: {date}\\nTime: {time}\\nCustomer Email: {customer_email}\\n\\nPlease follow up."
        msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
            <h2 style="color: #4f46e5;">New Demo Scheduled</h2>
            <p><strong>Action Required:</strong> A new demo has been scheduled.</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; width: 35%;">Date</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Time</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{time}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Submitter's Email</td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><a href="mailto:{customer_email}" style="color: #4f46e5;">{customer_email}</a></td>
                </tr>
            </table>
            <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
            <p style="font-size: 12px; color: #777;">Automated message from your SkillVerify System.</p>
        </div>
        '''
        mail.send(msg)"""
content = content.replace(block4_old, block4_new)


# Replace block 5 (Demo Customer)
block5_old = """            msg_customer.body = f"Hi there,\\n\\nYour demo request has been successfully scheduled.\\n\\nDate: {date}\\nTime: {time}\\n\\nOur team will reach out to you shortly with more details.\\n\\nBest regards,\\nThe SkillVerify Team"
            mail.send(msg_customer)"""
block5_new = """            msg_customer.body = f"Hi there,\\n\\nYour demo request has been successfully scheduled.\\n\\nDate: {date}\\nTime: {time}\\n\\nOur team will reach out to you shortly with more details.\\n\\nBest regards,\\nThe SkillVerify Team"
            msg_customer.html = f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; border: 1px solid #eaeaea; border-radius: 10px;">
                <h2 style="color: #4f46e5; text-align: center;">SkillVerify Demo Confirmation</h2>
                <p>Hello,</p>
                <p>Thank you for expressing interest in SkillVerify! Your demo request has been successfully scheduled.</p>
                <div style="background-color: #f9fafb; padding: 15px; border-radius: 8px; margin: 20px 0; border: 1px solid #e5e7eb;">
                    <p style="margin: 5px 0;"><strong>Scheduled Date:</strong> {date}</p>
                    <p style="margin: 5px 0;"><strong>Scheduled Time:</strong> {time}</p>
                </div>
                <p>One of our team members will review your request and connect with you shortly with further instructions and the meeting link.</p>
                <hr style="border: none; border-top: 1px solid #eaeaea; margin: 20px 0;">
                <p style="font-size: 12px; color: #777; text-align: center;">We look forward to speaking with you!</p>
                <p style="font-size: 12px; color: #777; text-align: center;">Best regards,<br><strong>The SkillVerify Team</strong></p>
            </div>
            '''
            mail.send(msg_customer)"""
content = content.replace(block5_old, block5_new)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated successfully!")
